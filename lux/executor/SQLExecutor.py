import pandas
from lux.vis.VisList import VisList
from lux.vis.Vis import Vis
from lux.core.frame import LuxDataFrame
from lux.executor.Executor import Executor
from lux.utils import utils
from lux.utils.utils import check_import_lux_widget, check_if_id_like

import math

class SQLExecutor(Executor):
    """
    Given a Vis objects with complete specifications, fetch and process data using SQL operations.
    """
    def __init__(self):
        self.name = "Executor"
        self.selection = []
        self.tables = []
        self.filters = ""

    def __repr__(self):
        return f"<Executor>"

    @staticmethod
    def execute(view_collection:VisList, ldf: LuxDataFrame):
        '''
        Given a VisList, fetch the data required to render the view
        1) Apply filters
        2) Retreive relevant attribute
        3) return a DataFrame with relevant results
        '''
        for view in view_collection:
            # Select relevant data based on attribute information
            attributes = set([])
            for clause in view._inferred_intent:
                if (clause.attribute):
                    if (clause.attribute=="Record"):
                        attributes.add(clause.attribute)
                    #else:
                    attributes.add(clause.attribute)
            if view.mark not in ["bar", "line", "histogram"]:
                where_clause, filterVars = SQLExecutor.execute_filter(view)
                required_variables = attributes | set(filterVars)
                required_variables = ",".join(required_variables)
                row_count = list(pandas.read_sql("SELECT COUNT(*) FROM {} {}".format(ldf.table_name, where_clause), ldf.SQLconnection)['count'])[0]
                if row_count > 10000:
                    query = "SELECT {} FROM {} {} ORDER BY random() LIMIT 10000".format(required_variables, ldf.table_name, where_clause)
                else:
                    query = "SELECT {} FROM {} {}".format(required_variables, ldf.table_name, where_clause)
                data = pandas.read_sql(query, ldf.SQLconnection)
                view._vis_data = utils.pandas_to_lux(data)
            if (view.mark =="bar" or view.mark =="line"):
                SQLExecutor.execute_aggregate(view, ldf)
            elif (view.mark =="histogram"):
                SQLExecutor.execute_binning(view, ldf)

    @staticmethod
    def execute_aggregate(view:Vis, ldf:LuxDataFrame, isFiltered = True):
        x_attr = view.get_attr_by_channel("x")[0]
        y_attr = view.get_attr_by_channel("y")[0]
        has_color = False
        groupby_attr =""
        measure_attr =""
        if (x_attr.aggregation is None or y_attr.aggregation is None):
            return
        if (y_attr.aggregation!=""):
            groupby_attr = x_attr
            measure_attr = y_attr
            agg_func = y_attr.aggregation
        if (x_attr.aggregation!=""):
            groupby_attr = y_attr
            measure_attr = x_attr
            agg_func = x_attr.aggregation
        if (groupby_attr.attribute in ldf.unique_values.keys()):
            attr_unique_vals = ldf.unique_values[groupby_attr.attribute]
        #checks if color is specified in the Vis
        if len(view.get_attr_by_channel("color")) == 1:
            color_attr = view.get_attr_by_channel("color")[0]
            color_attr_vals = ldf.unique_values[color_attr.attribute]
            color_cardinality = len(color_attr_vals)
            #NOTE: might want to have a check somewhere to not use categorical variables with greater than some number of categories as a Color variable----------------
            has_color = True
        else:
            color_cardinality = 1
        if (measure_attr!=""):
            #barchart case, need count data for each group
            if (measure_attr.attribute=="Record"):
                where_clause, filterVars = SQLExecutor.execute_filter(view)
                if has_color:
                    count_query = "SELECT {}, {}, COUNT({}) FROM {} {} GROUP BY {}, {}".format(groupby_attr.attribute, color_attr.attribute, groupby_attr.attribute, ldf.table_name, where_clause, groupby_attr.attribute, color_attr.attribute)
                    view._vis_data = pandas.read_sql(count_query, ldf.SQLconnection)
                    view._vis_data = view._vis_data.rename(columns={"count":"Record"})
                    view._vis_data = utils.pandas_to_lux(view._vis_data)
                else:
                    count_query = "SELECT {}, COUNT({}) FROM {} {} GROUP BY {}".format(groupby_attr.attribute, groupby_attr.attribute, ldf.table_name, where_clause, groupby_attr.attribute)
                    view._vis_data = pandas.read_sql(count_query, ldf.SQLconnection)
                    view._vis_data = view._vis_data.rename(columns={"count":"Record"})
                    view._vis_data = utils.pandas_to_lux(view._vis_data)
            #aggregate barchart case, need aggregate data for each group
            else:
                where_clause, filterVars = SQLExecutor.execute_filter(view)
                if has_color:
                    if agg_func == "mean":
                        mean_query = "SELECT {}, {}, AVG({}) as {} FROM {} {} GROUP BY {}, {}".format(groupby_attr.attribute, color_attr.attribute, measure_attr.attribute, measure_attr.attribute, ldf.table_name, where_clause, groupby_attr.attribute, color_attr.attribute)
                        view._vis_data = pandas.read_sql(mean_query, ldf.SQLconnection)
                        view._vis_data = utils.pandas_to_lux(view._vis_data)
                    if agg_func == "sum":
                        mean_query = "SELECT {}, {}, SUM({}) as {} FROM {} {} GROUP BY {}, {}".format(groupby_attr.attribute, color_attr.attribute, measure_attr.attribute, measure_attr.attribute, ldf.table_name, where_clause, groupby_attr.attribute, color_attr.attribute)
                        view._vis_data = pandas.read_sql(mean_query, ldf.SQLconnection)
                        view._vis_data = utils.pandas_to_lux(view._vis_data)
                    if agg_func == "max":
                        mean_query = "SELECT {}, {}, MAX({}) as {} FROM {} {} GROUP BY {}, {}".format(groupby_attr.attribute, color_attr.attribute, measure_attr.attribute, measure_attr.attribute, ldf.table_name, where_clause, groupby_attr.attribute, color_attr.attribute)
                        view._vis_data = pandas.read_sql(mean_query, ldf.SQLconnection)
                        view._vis_data = utils.pandas_to_lux(view._vis_data)
                else:
                    if agg_func == "mean":
                        mean_query = "SELECT {}, AVG({}) as {} FROM {} {} GROUP BY {}".format(groupby_attr.attribute, measure_attr.attribute, measure_attr.attribute, ldf.table_name, where_clause, groupby_attr.attribute)
                        view._vis_data = pandas.read_sql(mean_query, ldf.SQLconnection)
                        view._vis_data = utils.pandas_to_lux(view._vis_data)
                    if agg_func == "sum":
                        mean_query = "SELECT {}, SUM({}) as {} FROM {} {} GROUP BY {}".format(groupby_attr.attribute, measure_attr.attribute, measure_attr.attribute, ldf.table_name, where_clause, groupby_attr.attribute)
                        view._vis_data = pandas.read_sql(mean_query, ldf.SQLconnection)
                        view._vis_data = utils.pandas_to_lux(view._vis_data)
                    if agg_func == "max":
                        mean_query = "SELECT {}, MAX({}) as {} FROM {} {} GROUP BY {}".format(groupby_attr.attribute, measure_attr.attribute, measure_attr.attribute, ldf.table_name, where_clause, groupby_attr.attribute)
                        view._vis_data = pandas.read_sql(mean_query, ldf.SQLconnection)
                        view._vis_data = utils.pandas_to_lux(view._vis_data)
            result_vals = list(view._vis_data[groupby_attr.attribute])
            #create existing group by attribute combinations if color is specified
            #this is needed to check what combinations of group_by_attr and color_attr values have a non-zero number of elements in them
            if has_color:
                res_color_combi_vals = []
                result_color_vals = list(view._vis_data[color_attr.attribute])
                for i in range(0, len(result_vals)):
                    res_color_combi_vals.append([result_vals[i], result_color_vals[i]])
            # For filtered aggregation that have missing groupby-attribute values, set these aggregated value as 0, since no datapoints
            if (isFiltered or has_color and attr_unique_vals):
                N_unique_vals = len(attr_unique_vals)
                if (len(result_vals) != N_unique_vals*color_cardinality):    
                    columns = view._vis_data.columns
                    if has_color:
                        df = pandas.DataFrame({columns[0]: attr_unique_vals*color_cardinality, columns[1]: pandas.Series(color_attr_vals).repeat(N_unique_vals)})
                        view._vis_data = view._vis_data.merge(df, on=[columns[0],columns[1]], how='right', suffixes=['', '_right'])
                        for col in columns[2:]:
                            view._vis_data[col] = view._vis_data[col].fillna(0) #Triggers __setitem__
                        assert len(list(view._vis_data[groupby_attr.attribute])) == N_unique_vals*len(color_attr_vals), f"Aggregated data missing values compared to original range of values of `{groupby_attr.attribute, color_attr.attribute}`."
                        view._vis_data = view._vis_data.iloc[:,:3] # Keep only the three relevant columns not the *_right columns resulting from merge
                    else:
                        df = pandas.DataFrame({columns[0]: attr_unique_vals})
                        
                        view._vis_data = view._vis_data.merge(df, on=columns[0], how='right', suffixes=['', '_right'])

                        for col in columns[1:]:
                            view._vis_data[col] = view._vis_data[col].fillna(0)
                        assert len(list(view._vis_data[groupby_attr.attribute])) == N_unique_vals, f"Aggregated data missing values compared to original range of values of `{groupby_attr.attribute}`."
            view._vis_data = view._vis_data.sort_values(by=groupby_attr.attribute, ascending=True)
            view._vis_data = view._vis_data.reset_index()
            view._vis_data = view._vis_data.drop(columns="index")

    @staticmethod
    def execute_binning(view:Vis, ldf:LuxDataFrame):
        import numpy as np
        bin_attribute = list(filter(lambda x: x.bin_size!=0,view._inferred_intent))[0]

        num_bins = bin_attribute.bin_size
        attr_min = min(ldf.unique_values[bin_attribute.attribute])
        attr_max = max(ldf.unique_values[bin_attribute.attribute])
        attr_type = type(ldf.unique_values[bin_attribute.attribute][0])

        #get filters if available
        where_clause, filterVars = SQLExecutor.execute_filter(view)
        #need to calculate the bin edges before querying for the relevant data
        bin_width = (attr_max-attr_min)/num_bins
        upper_edges = []
        for e in range(1, num_bins):
            curr_edge = attr_min + e*bin_width
            if attr_type == int:
                upper_edges.append(str(math.ceil(curr_edge)))
            else:
                upper_edges.append(str(curr_edge))
        upper_edges = ",".join(upper_edges)
        view_filter, filter_vars = SQLExecutor.execute_filter(view)
        bin_count_query = "SELECT width_bucket, COUNT(width_bucket) FROM (SELECT width_bucket({}, '{}') FROM {} {}) as Buckets GROUP BY width_bucket ORDER BY width_bucket".format(bin_attribute.attribute, '{'+upper_edges+'}', ldf.table_name, where_clause)
        bin_count_data = pandas.read_sql(bin_count_query, ldf.SQLconnection)

        #counts,binEdges = np.histogram(ldf[bin_attribute.attribute],bins=bin_attribute.bin_size)
        #binEdges of size N+1, so need to compute binCenter as the bin location
        upper_edges = [float(i) for i in upper_edges.split(",")]
        if attr_type == int:
            bin_centers = np.array([math.ceil((attr_min+attr_min+bin_width)/2)])
        else:
            bin_centers = np.array([(attr_min+attr_min+bin_width)/2])
        bin_centers = np.append(bin_centers, np.mean(np.vstack([upper_edges[0:-1],upper_edges[1:]]), axis=0))
        if attr_type == int:
            bin_centers = np.append(bin_centers, math.ceil((upper_edges[len(upper_edges)-1]+attr_max)/2))
        else:
            bin_centers = np.append(bin_centers, (upper_edges[len(upper_edges)-1]+attr_max)/2)

        if len(bin_centers) > len(bin_count_data):
            bucket_lables = bin_count_data['width_bucket'].unique()
            for i in range(0,len(bin_centers)):
                if i not in bucket_lables:
                    bin_count_data = bin_count_data.append(pandas.DataFrame([[i,0]], columns = bin_count_data.columns))
        view._vis_data = pandas.DataFrame(np.array([bin_centers,list(bin_count_data['count'])]).T,columns=[bin_attribute.attribute, "Number of Records"])
        view._vis_data = utils.pandas_to_lux(view.data)
        
    @staticmethod
    #takes in a view and returns an appropriate SQL WHERE clause that based on the filters specified in the view's _inferred_intent
    def execute_filter(view:Vis):
        where_clause = []
        filters = utils.get_filter_specs(view._inferred_intent)
        filter_vars = []
        if (filters):
            for f in range(0,len(filters)):
                if f == 0:
                    where_clause.append("WHERE")
                else:
                    where_clause.append("AND")
                where_clause.extend([str(filters[f].attribute), str(filters[f].filter_op), "'" + str(filters[f].value) + "'"])
                if filters[f].attribute not in filter_vars:
                    filter_vars.append(filters[f].attribute)
        if where_clause == []:
            return("", [])
        else:
            where_clause = " ".join(where_clause)
        return(where_clause, filter_vars)


    #######################################################
    ########## Metadata, type, model schema ###########
    #######################################################

    def compute_dataset_metadata(self, ldf:LuxDataFrame):
        self.get_SQL_attributes(ldf)
        for attr in list(ldf.columns):
            ldf[attr] = None
        ldf.data_type_lookup = {}
        ldf.data_type = {}
        #####NOTE: since we aren't expecting users to do much data processing with the SQL database, should we just keep this 
        #####      in the initialization and do it just once
        self.compute_data_type(ldf)
        self.compute_stats(ldf)
        ldf.data_model_lookup = {}
        ldf.data_model = {}
        self.compute_data_model(ldf)

    def get_SQL_attributes(self, ldf:LuxDataFrame):
        if "." in ldf.table_name:
            table_name = ldf.table_name[self.table_name.index(".")+1:]
        else:
            table_name = ldf.table_name
        attr_query = "SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS where TABLE_NAME = '{}'".format(table_name)
        attributes = list(pandas.read_sql(attr_query, ldf.SQLconnection)['column_name'])
        for attr in attributes:
            ldf[attr] = None

    def compute_stats(self, ldf:LuxDataFrame):
        # precompute statistics
        ldf.unique_values = {}
        ldf._min_max = {}

        self.get_unique_values(ldf)
        #ldf.get_cardinality()
        for attribute in ldf.columns:
            if ldf.data_type_lookup[attribute] == 'quantitative':
                min_max_query = pandas.read_sql("SELECT MIN({}) as min, MAX({}) as max FROM {}".format(attribute, attribute, ldf.table_name), ldf.SQLconnection)
                ldf._min_max[attribute] = (list(min_max_query["min"])[0], list(min_max_query['max'])[0])

    def get_cardinality(self, ldf:LuxDataFrame):
        cardinality = {}
        for attr in list(ldf.columns):
            card_query = pandas.read_sql("SELECT Count(Distinct({})) FROM {}".format(attr, ldf.table_name), ldf.SQLconnection)
            cardinality[attr] = list(card_query["count"])[0]
        ldf.cardinality = cardinality

    def get_unique_values(self, ldf:LuxDataFrame):
        unique_vals = {}
        for attr in list(ldf.columns):
            unique_query = pandas.read_sql("SELECT Distinct({}) FROM {}".format(attr, ldf.table_name), ldf.SQLconnection)
            unique_vals[attr] = list(unique_query[attr])
        ldf.unique_values = unique_vals

    def compute_data_type(self, ldf:LuxDataFrame):
        data_type_lookup = {}
        sql_dtypes = {}
        self.get_cardinality(ldf)
        if "." in ldf.table_name:
            table_name = ldf.table_name[ldf.table_name.index(".")+1:]
        else:
            table_name = ldf.table_name
        #get the data types of the attributes in the SQL table
        for attr in list(ldf.columns):
            datatype_query = "SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{}' AND COLUMN_NAME = '{}'".format(table_name, attr)
            datatype = list(pandas.read_sql(datatype_query, ldf.SQLconnection)['data_type'])[0]
            sql_dtypes[attr] = datatype

        data_type = {"quantitative":[], "ordinal":[], "nominal":[], "temporal":[], "id":[]}
        for attr in list(ldf.columns):
            if str(attr).lower() in ["month", "year"]:
                data_type_lookup[attr] = "temporal"
                data_type["temporal"].append(attr)
            elif sql_dtypes[attr] in ["character", "character varying", "boolean", "uuid", "text"]:
                data_type_lookup[attr] = "nominal"
                data_type["nominal"].append(attr)
            elif sql_dtypes[attr] in ["integer", "numeric", "decimal", "bigint", "real", "smallint", "smallserial", "serial"]:
                if ldf.cardinality[attr] < 13:
                    data_type_lookup[attr] = "nominal"
                    data_type["nominal"].append(attr)
                elif check_if_id_like(ldf,attr): 
                    ldf.data_type_lookup[attr] = "id"
                else:
                    data_type_lookup[attr] = "quantitative"
                    data_type["quantitative"].append(attr)
            elif "time" in sql_dtypes[attr] or "date" in sql_dtypes[attr]:
                data_type_lookup[attr] = "temporal"
                data_type["temporal"].append(attr)
        ldf.data_type_lookup = data_type_lookup
        ldf.data_type = data_type

    def compute_data_model(self, ldf:LuxDataFrame):
        ldf.data_model = {
            "measure": ldf.data_type["quantitative"],
            "dimension": ldf.data_type["ordinal"] + ldf.data_type["nominal"] + ldf.data_type["temporal"]
        }
        ldf.data_model_lookup = ldf.executor.reverseMapping(ldf.data_model)