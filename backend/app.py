from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

app = Flask(__name__)
CORS(app)

# Өгөгдлийн сангийн холболт
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@postgis:5432/gisdb'
)
 
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


@app.route('/api/aimags', methods=['GET'])
def get_aimags():
    """Бүх аймгуудын хил"""
    session = Session()
    try:
        query = text("""
            SELECT 
                gid,
                name_1 as name,
                ST_AsGeoJSON(geom) as geometry
            FROM gadm41_mng_1
            ORDER BY name_1
        """)
        result = session.execute(query)
        
        aimags = []
        for row in result:
            import json
            aimags.append({
                'id': row.gid,
                'name': row.name,
                'geometry': json.loads(row.geometry)
            })
        
        return jsonify(aimags)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/aimags/<int:aimag_id>/sums', methods=['GET'])
def get_sums_by_aimag(aimag_id):
    """Тодорхой аймгийн бүх сумууд"""
    session = Session()
    try:
        query = text("""
            SELECT 
                s.gid,
                s.name_2 as name,
                ST_AsGeoJSON(s.geom) as geometry,
                ST_AsGeoJSON(ST_Centroid(s.geom)) as center
            FROM gadm41_mng_2 s
            JOIN gadm41_mng_1 a ON s.gid_1 = a.gid_1
            WHERE a.gid = :aimag_id
            ORDER BY s.name_2
        """)
        result = session.execute(query, {'aimag_id': aimag_id})
        
        sums = []
        for row in result:
            import json
            sums.append({
                'id': row.gid,
                'name': row.name,
                'geometry': json.loads(row.geometry),
                'center': json.loads(row.center)
            })
        
        return jsonify(sums)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/sums', methods=['GET'])
def get_all_sums():
    """Бүх сумууд аймгийн нэртэй, хилтэй"""
    session = Session()
    try:
        query = text("""
            SELECT 
                s.gid,
                s.name_2 as sum_name,
                a.name_1 as aimag_name,
                a.gid as aimag_id,
                ST_AsGeoJSON(s.geom) as geometry,
                ST_AsGeoJSON(ST_Centroid(s.geom)) as center
            FROM gadm41_mng_2 s
            JOIN gadm41_mng_1 a ON s.gid_1 = a.gid_1
            ORDER BY a.name_1, s.name_2
        """)
        result = session.execute(query)
        
        sums = []
        for row in result:
            import json
            sums.append({
                'id': row.gid,
                'sum_name': row.sum_name,
                'aimag_name': row.aimag_name,
                'aimag_id': row.aimag_id,
                'geometry': json.loads(row.geometry),
                'center': json.loads(row.center)
            })
        
        return jsonify(sums)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/sums/<int:sum_id>', methods=['GET'])
def get_sum_by_id(sum_id):
    """ID-аар тодорхой сум"""
    session = Session()
    try:
        query = text("""
            SELECT 
                s.gid,
                s.name_2 as sum_name,
                a.name_1 as aimag_name,
                a.gid as aimag_id,
                ST_AsGeoJSON(s.geom) as geometry,
                ST_AsGeoJSON(ST_Centroid(s.geom)) as center
            FROM gadm41_mng_2 s
            JOIN gadm41_mng_1 a ON s.gid_1 = a.gid_1
            WHERE s.gid = :sum_id
        """)
        result = session.execute(query, {'sum_id': sum_id})
        
        row = result.fetchone()
        if not row:
            return jsonify({'error': 'Сум олдсонгүй'}), 404
        
        import json
        sum_data = {
            'id': row.gid,
            'sum_name': row.sum_name,
            'aimag_name': row.aimag_name,
            'aimag_id': row.aimag_id,
            'geometry': json.loads(row.geometry),
            'center': json.loads(row.center)
        }
        
        return jsonify(sum_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/aimags/<int:aimag_id>/sums/centers', methods=['GET'])
def get_sum_centers_by_aimag(aimag_id):
    """Тодорхой аймгийн сумуудын нэр ба төвийн координат"""
    session = Session()
    try:
        query = text("""
            SELECT 
                s.name_2 as sum_name,
                ST_X(ST_Centroid(s.geom)) as longitude,
                ST_Y(ST_Centroid(s.geom)) as latitude
            FROM gadm41_mng_2 s
            JOIN gadm41_mng_1 a ON s.gid_1 = a.gid_1
            WHERE a.gid = :aimag_id
            ORDER BY s.name_2
        """)
        result = session.execute(query, {'aimag_id': aimag_id})
        
        sums = []
        for row in result:
            sums.append({
                'sum_name': row.sum_name,
                'longitude': float(row.longitude),
                'latitude': float(row.latitude)
            })
        
        return jsonify(sums)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/search', methods=['GET'])
def search_locations():
    """Аймаг, сумын нэрээр хайх"""
    query_param = request.args.get('q', '')
    if not query_param:
        return jsonify([])
    
    session = Session()
    try:
        # Аймгуудыг хайх
        aimag_query = text("""
            SELECT 
                gid,
                name_1 as name,
                'aimag' as type
            FROM gadm41_mng_1
            WHERE LOWER(name_1) LIKE LOWER(:query)
            ORDER BY name_1
        """)
        
        # Сумуудыг хайх
        sum_query = text("""
            SELECT 
                s.gid,
                s.name_2 || ', ' || a.name_1 as name,
                'sum' as type,
                a.gid as aimag_id
            FROM gadm41_mng_2 s
            JOIN gadm41_mng_1 a ON s.gid_1 = a.gid_1
            WHERE LOWER(s.name_2) LIKE LOWER(:query) 
               OR LOWER(a.name_1) LIKE LOWER(:query)
            ORDER BY a.name_1, s.name_2
        """)
        
        search_pattern = f'%{query_param}%'
        
        aimag_results = session.execute(aimag_query, {'query': search_pattern})
        sum_results = session.execute(sum_query, {'query': search_pattern})
        
        results = []
        
        for row in aimag_results:
            results.append({
                'id': row.gid,
                'name': row.name,
                'type': row.type
            })
        
        for row in sum_results:
            results.append({
                'id': row.gid,
                'name': row.name,
                'type': row.type,
                'aimag_id': row.aimag_id if hasattr(row, 'aimag_id') else None
            })
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/health', methods=['GET'])
def health():
    """Эрүүл мэндийн шалгалт endpoint"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
